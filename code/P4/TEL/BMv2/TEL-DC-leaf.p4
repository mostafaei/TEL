/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

const bit<16> TYPE_IPV4 = 0x800;

/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;

#define PORTS 4


register<bit<9>>(1) ports_status_r;
register<bit<1>>(PORTS) failed_port;

header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

header ipv4_t {
    bit<4>    version;
    bit<4>    ihl;
    bit<8>    diffserv;
    bit<16>   totalLen;
    bit<16>   identification;
    bit<3>    flags;
    bit<13>   fragOffset;
    bit<8>    ttl;
    bit<8>    protocol;
    bit<16>   hdrChecksum;
    ip4Addr_t srcAddr;
    ip4Addr_t dstAddr;
}

header myTunnel_t {
    bit<16> hops; // number of hops for the packet
    bit<8>   path_length;
}

header tcp_t{
    bit<16> srcPort;
    bit<16> dstPort;
    bit<32> seqNo;
    bit<32> ackNo;
    bit<4>  dataOffset;
    bit<4>  res;
    bit<1>  cwr;
    bit<1>  ece;
    bit<1>  urg;
    bit<1>  ack;
    bit<1>  psh;
    bit<1>  rst;
    bit<1>  syn;
    bit<1>  fin;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgentPtr;
}

struct metadata {
    bit<9>   starting_port;
    bit<9>   out_port; // this is to check the egress port
    bit<9>   all_ports; //all ports 
    bit<9>   out_port_xor; 
    bit<9>   mod_counter;
    bit<9>   check_failure;  //to check if the link failed if(0b111 ^ port_status_r != 0) => failure

    bit<14> ecmp_hash;
    bit<14> ecmp_group_id;
    bit<1>  final_dst;
    bit<4>  dst_id;
    bit<9>  TEL_rnd;


    /* empty */
}

struct headers {
    ethernet_t   ethernet;
    myTunnel_t   myTunnel;
    ipv4_t       ipv4;
    tcp_t        tcp;
}

/*************************************************************************
*********************** P A R S E R  ***********************************
*************************************************************************/

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {

    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_IPV4: parse_ipv4;
            default: accept;
        }
    }

    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition accept;
    }

    state parse_tcp {
        packet.extract(hdr.tcp);
        transition accept;
    }

}

/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {   
    apply {  }
}


/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {
    action drop() {
        mark_to_drop(standard_metadata);
    }

    action ecmp_group(bit<14> ecmp_group_id, bit<16> num_nhops){
        hash(meta.ecmp_hash,
        HashAlgorithm.crc16,
        (bit<1>)0,
        { hdr.ipv4.srcAddr,
          hdr.ipv4.dstAddr,
          hdr.tcp.srcPort,
          hdr.tcp.dstPort,
          hdr.ipv4.protocol},
        num_nhops);

        meta.ecmp_group_id = ecmp_group_id;
    }

    action set_nhop(macAddr_t dstAddr, egressSpec_t port) {
        //set the src mac address as the previous dst, this is not correct right?
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
       //set the destination mac address that we got from the match in the table
        hdr.ethernet.dstAddr = dstAddr;
        //set the output port that we also get from the table
        standard_metadata.egress_spec = port;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }

    table ecmp_group_to_nhop {
        key = {
            meta.ecmp_group_id:    exact;
            meta.ecmp_hash: exact;
        }
        actions = {
            drop;
            set_nhop;
        }
        size = 1024;
    }

    table ipv4_lpm_failure {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            //set_nhop;
            ecmp_group;
            drop;
        }
        size = 1024;
        default_action = drop;
    }

    table ipv4_lpm {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            set_nhop;
            ecmp_group;
            drop;
        }
        size = 1024;
        default_action = drop;
    }
    
    action set_if_status(egressSpec_t _value) {
        meta.out_port=_value;
        meta.mod_counter=_value;
    }
   
   action set_starting_port(egressSpec_t port_start) {
        meta.starting_port= port_start;
        ports_status_r.read(meta.all_ports, 0 );
    }

    action send_pkt(egressSpec_t port_to_send) {
       standard_metadata.egress_spec= port_to_send;
       hdr.myTunnel.path_length = hdr.myTunnel.path_length + 1;
    }

    action xor_outport(egressSpec_t _all_ports) {
      ports_status_r.read(meta.all_ports, 0 );
      meta.out_port_xor= meta.all_ports ^ _all_ports;
    }

    action set_RR () {
        //meta.mod_counter=0;
        // since we have end-hosts connected to leaf switches and based on
        // the number of ports we have to add that value when doing mod operation
        meta.out_port=(bit<9>)(meta.mod_counter % PORTS) + PORTS + 1;
    }

    action set_default_route(egressSpec_t send_to) {
      meta.out_port=send_to;
      meta.mod_counter=send_to;
      standard_metadata.egress_spec = send_to;
    }

    table default_route {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            set_nhop;
            drop;
        }
        size = 1024;
        default_action = drop;
    }

    table rotor {
        actions = {
           set_RR;
        }
    }

    table check_outport_status {
        key = {
            hdr.ethernet.etherType: exact;
            }
        actions = {
            xor_outport;
        }
    }

    table if_status {
        key = {
            meta.out_port_xor: ternary;
        }
        actions = {
            set_if_status;
        }
        size = 1024;
    }

    table set_egress_port {
        key = {
            meta.out_port: exact;
        }
        actions = {
            set_starting_port;
        }
        size = 1024;
    }

    table route_pkt {
        key = {
            meta.starting_port: ternary;
            meta.all_ports: ternary;
        }
        actions = {
            send_pkt;
        }
        size = 1024;
    }
    table TEL_route_pkt {
        key = {
            meta.ecmp_group_id:    exact;
            meta.all_ports: exact;

        }
        actions = {
            set_nhop;
        }
        size = 1024;
    }/*
    table TEL_route_pkt {
        key = {
            meta.TEL_rnd: exact;

        }
        actions = {
            set_nhop;
        }
        size = 1024;
    }*/

    apply {
        if (hdr.ipv4.isValid()) {
            ports_status_r.read(meta.all_ports, 0 );
            check_outport_status.apply();

            //ECMP working version end
            if(!default_route.apply().hit)
            {

                if (meta.out_port_xor == 0 ) {
                    switch (ipv4_lpm.apply().action_run){
                    ecmp_group: {
                        ecmp_group_to_nhop.apply();
                        }
                    }
                }
                else
                {
                	ipv4_lpm_failure.apply();
                    TEL_route_pkt.apply();
                }
            }
        }
    }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply {  }
}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers  hdr, inout metadata meta) {
     apply {
	update_checksum(
	    hdr.ipv4.isValid(),
            { hdr.ipv4.version,
	      hdr.ipv4.ihl,
              hdr.ipv4.diffserv,
              hdr.ipv4.totalLen,
              hdr.ipv4.identification,
              hdr.ipv4.flags,
              hdr.ipv4.fragOffset,
              hdr.ipv4.ttl,
              hdr.ipv4.protocol,
              hdr.ipv4.srcAddr,
              hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16);
    }
}

/*************************************************************************
***********************  D E P A R S E R  *******************************
*************************************************************************/

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
        packet.emit(hdr.tcp);
    }
}

/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

V1Switch(
MyParser(),
MyVerifyChecksum(),
MyIngress(),
MyEgress(),
MyComputeChecksum(),
MyDeparser()
) main;
