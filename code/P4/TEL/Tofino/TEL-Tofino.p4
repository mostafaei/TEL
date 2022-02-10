/* -*- P4_16 -*- */

#include <core.p4>
#include <tna.p4>
const bit<16> TYPE_IPV4 = 0x800;


/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/
typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;


const int PORTS=4;


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

struct my_ingress_headers_t {
    ethernet_t   ethernet;
    myTunnel_t   myTunnel;
    ipv4_t       ipv4;
    tcp_t        tcp;
}

    /******  G L O B A L   I N G R E S S   M E T A D A T A  *********/

struct my_ingress_metadata_t {
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

    /***********************  P A R S E R  **************************/
parser IngressParser(packet_in        pkt,
    /* User */    
    out my_ingress_headers_t          hdr,
    out my_ingress_metadata_t         meta,
    /* Intrinsic */
    out ingress_intrinsic_metadata_t  ig_intr_md)
{
    /* This is a mandatory state, required by Tofino Architecture */
     state start {
        pkt.extract(ig_intr_md);
        pkt.advance(PORT_METADATA_SIZE);
        transition parse_ethernet;
    }

    state parse_ethernet {
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_IPV4: parse_ipv4;
            default: accept;
        }
    }

    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        transition accept;
    }

   state parse_tcp {
        pkt.extract(hdr.tcp);
        transition accept;
    }
}

    /***************** M A T C H - A C T I O N  *********************/

control Ingress(
    /* User */
    inout my_ingress_headers_t                       hdr,
    inout my_ingress_metadata_t                      meta,
    /* Intrinsic */
    in    ingress_intrinsic_metadata_t               ig_intr_md,
    in    ingress_intrinsic_metadata_from_parser_t   ig_prsr_md,
    inout ingress_intrinsic_metadata_for_deparser_t  ig_dprsr_md,
    inout ingress_intrinsic_metadata_for_tm_t        ig_tm_md)
{
    action send(PortId_t port) {
        ig_tm_md.ucast_egress_port = port;

    }

    action drop() {
        ig_dprsr_md.drop_ctl = 1;
    }

  bit<16> port_status;
    Register<bit<16>, bit<32>>(32w1) port_status_reg;
    RegisterAction<bit<16>, bit<32>, bit<16>>(port_status_reg) port_status_reg_read = {
       void apply(inout bit<16> value, out bit<16> read_value){
            read_value = value;
        }
    };


    Hash<bit<14>>(HashAlgorithm_t.CRC16) hash;
    action ecmp_group(bit<14> ecmp_group_id, bit<16> num_nhops){
        meta.ecmp_hash=hash.get({hdr.ipv4.srcAddr,
          hdr.ipv4.dstAddr,
          hdr.tcp.srcPort,
          hdr.tcp.dstPort,
	hdr.ipv4.protocol});
       meta.ecmp_group_id = ecmp_group_id;
    }

    /*action ecmp_group(bit<14> ecmp_group_id, bit<16> num_nhops){
        hash(meta.ecmp_hash,
        HashAlgorithm.crc16,
        (bit<1>)0,
        { hdr.ipv4.srcAddr,
          hdr.ipv4.dstAddr,
          hdr.tcp.srcPort,
          hdr.tcp.dstP,
	hdr.ipv4.protocol},
        num_nhops);
       meta.ecmp_group_id = ecmp_group_id;
    }*/

    action set_nhop(PortId_t port) {
        ig_tm_md.ucast_egress_port = port;
    }
   /*action set_nhop(macAddr_t dstAddr, egressSpec_t port) {
        //set the src mac address as the previous dst, this is not correct right?
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
       //set the destination mac address that we got from the match in the table
        hdr.ethernet.dstAddr = dstAddr;
        //set the output port that we also get from the table
        standard_metadata.egress_spec = port;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }*/
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

    table ipv4_lpm {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            set_nhop;
            //ecmp_group;
            drop;
        }
        size = 1024;
        default_action = drop;
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

    action set_if_status(egressSpec_t _value) {
        meta.out_port=_value;
        meta.mod_counter=_value;
    }
   
   action set_starting_port(egressSpec_t port_start) {
        meta.starting_port= port_start;
        port_status_reg_read.execute(0);
        //ports_status_r.read(meta.all_ports, 0 );
    }

    action send_pkt(egressSpec_t port_to_send) {
       //standard_metadata.egress_spec= port_to_send;
	ig_tm_md.ucast_egress_port = port_to_send;
       hdr.myTunnel.path_length = hdr.myTunnel.path_length + 1;
    }
   action xor_outport(egressSpec_t _all_ports) {   
      meta.out_port_xor= meta.all_ports ^ _all_ports;
      meta.TEL_rnd=meta.out_port_xor;
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
      ig_tm_md.ucast_egress_port = send_to;
      //standard_metadata.egress_spec = send_to;
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
    }
    apply {
        if (hdr.ipv4.isValid()) {
            //ports_status_r.read(meta.all_ports, 0 );
	    port_status = port_status_reg_read.execute(0);
            check_outport_status.apply();
            //ECMP working version end
            //if(!default_route.apply().hit)
            //{

               if (meta.out_port_xor == 0 ) {
                    ipv4_lpm.apply();
                }
                else
                {
                    ipv4_lpm_failure.apply();
                    TEL_route_pkt.apply(); 
          	    
                }
            //}
        }
    }

}



/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

    /*********************  D E P A R S E R  ************************/

    /*********************  D E P A R S E R  ************************/

control IngressDeparser(packet_out pkt,
    /* User */
    inout my_ingress_headers_t                       hdr,
    in    my_ingress_metadata_t                      meta,
    /* Intrinsic */
    in    ingress_intrinsic_metadata_for_deparser_t  ig_dprsr_md)
{
    apply {
        pkt.emit(hdr);
    }
}

/*************************************************************************
 ****************  E G R E S S   P R O C E S S I N G   *******************
 *************************************************************************/

    /***********************  H E A D E R S  ************************/

struct my_egress_headers_t {
}

    /********  G L O B A L   E G R E S S   M E T A D A T A  *********/

struct my_egress_metadata_t {
}

    /***********************  P A R S E R  **************************/

parser EgressParser(packet_in        pkt,
    /* User */
    out my_egress_headers_t          hdr,
    out my_egress_metadata_t         meta,
    /* Intrinsic */
    out egress_intrinsic_metadata_t  eg_intr_md)
{
    /* This is a mandatory state, required by Tofino Architecture */
    state start {
        pkt.extract(eg_intr_md);
        transition accept;
    }
}

    /***************** M A T C H - A C T I O N  *********************/

control Egress(
    /* User */
    inout my_egress_headers_t                          hdr,
    inout my_egress_metadata_t                         meta,
    /* Intrinsic */    
    in    egress_intrinsic_metadata_t                  eg_intr_md,
    in    egress_intrinsic_metadata_from_parser_t      eg_prsr_md,
    inout egress_intrinsic_metadata_for_deparser_t     eg_dprsr_md,
    inout egress_intrinsic_metadata_for_output_port_t  eg_oport_md)
{
    apply {
    }
}

    /*********************  D E P A R S E R  ************************/

control EgressDeparser(packet_out pkt,
    /* User */
    inout my_egress_headers_t                       hdr,
    in    my_egress_metadata_t                      meta,
    /* Intrinsic */
    in    egress_intrinsic_metadata_for_deparser_t  eg_dprsr_md)
{
    apply {
        pkt.emit(hdr);
    }
}


/************ F I N A L   P A C K A G E ******************************/
Pipeline(
    IngressParser(),
    Ingress(),
    IngressDeparser(),
    EgressParser(),
    Egress(),
    EgressDeparser()
) pipe;

Switch(pipe) main;
