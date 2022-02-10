/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

const bit<16> TYPE_MYTUNNEL = 0x1212;
const bit<16> TYPE_IPV4 = 0x800;

/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;

register<bit<16>>(4) hops_r;

header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

header myTunnel_t {
    bit<16> proto_id;
    bit<16> dst_id;
    bit<16> src_id; //index of register in destination hops_r register
    bit<16> hops_1; // number of hops for the packet
    bit<1> packet_seq; //DDC packet_seq
    bit<7> final_dst; //DDC packet_seq
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

struct metadata {
	bit<1> final_dst;
    /* empty */
}

struct headers {
    ethernet_t   ethernet;
    myTunnel_t   myTunnel;
    ipv4_t       ipv4;
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
            TYPE_MYTUNNEL: parse_myTunnel;
            TYPE_IPV4: parse_ipv4;
            default: accept;
        }
    }

    state parse_myTunnel {
        packet.extract(hdr.myTunnel);
        transition select(hdr.myTunnel.proto_id) {
            TYPE_IPV4: parse_ipv4;
            default: accept;
        }
    }

    state parse_ipv4 {
        packet.extract(hdr.ipv4);
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
    
	// register<bit<size of each entry>>(number of entries)
	register<bit<1>>(3) direction_r;
	register<bit<1>>(3) local_seq_r;
	register<bit<1>>(3) remote_seq_r;


	//port status
	register<bit<1>>(3) port_status_r;

	//: FIB update: reverse in to out action
	action flip_local_seq(bit<32> index) {
		bit<1> var;
		local_seq_r.read(var, index);
		var = var ^ 1; // XOR with 1, flips bit in var
		local_seq_r.write(index, var);
	}
	action reverse_in_to_out(bit<9> link) {
		//write '1' aka 'OUT' to the index of(incoming port no.)
		direction_r.write((bit<32>)link, 1);
		flip_local_seq((bit<32>)link);
	}
	action reverse_out_to_in(bit<9> link) {
		//write '0' aka 'IN' to the index of(incoming port no.)
		direction_r.write((bit<32>)link, 0);
		flip_local_seq((bit<32>)link);
	}

	action send_on_outlink(egressSpec_t port) {
        standard_metadata.egress_spec = port;
        hdr.myTunnel.hops_1 = hdr.myTunnel.hops_1 + 1;
        bit<1> localseq;
        local_seq_r.read(localseq,(bit<32>) port);
        hdr.myTunnel.packet_seq=localseq;
    }
	
	action drop() {
        mark_to_drop(standard_metadata);
    }

    //action ipv4_forward(macAddr_t dstAddr) {
    action ipv4_forward(macAddr_t dstAddr, egressSpec_t port) {
        standard_metadata.egress_spec = port;
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }
    
    action set_dst(bit<1> new_dst) {
        meta.final_dst=new_dst;
    }
 

    table ipv4_lpm {
        key = {
            meta.final_dst: exact;
        }
        actions = {
            ipv4_forward;
            drop;
            NoAction;
        }
        size = 1024;
        default_action = drop();
    }
    
    action myTunnel_forward(bit<1> dst) {
        meta.final_dst=dst;
    }

    table myTunnel_exact {
        key = {
            hdr.myTunnel.dst_id: exact;
        }
        actions = {
            myTunnel_forward;
            drop;
        }
        size = 1024;
        default_action = drop();
    }


    apply {
        if (hdr.myTunnel.isValid()) {
        	myTunnel_exact.apply();
        	///bit<1> tmp_prot=0;
        	//send normal traffic
        	// we check the direction and port status and forward the packets accordingly
        	/*bit<1> dir_1;*/
		
            bit<1> dir_2;
            bit<1> port_status_2;
            direction_r.read(dir_2, 2);
            port_status_r.read(port_status_2,2);
		


            bit<1> direction;
            bit<1> remoteseq;
            bit<1> port_status_n;
            bit<1> dir_n;
            //bit<1> port_status_out;
            direction_r.read(direction, (bit<32>)standard_metadata.ingress_port);
            //port_status_r.read(port_status_n,(bit<32>) standard_metadata.ingress_port);
            remote_seq_r.read(remoteseq,(bit<32>) standard_metadata.ingress_port);
            //port_status_r.read(port_status_out,(bit<32>) standard_metadata.egress_spec);
            
            /*this if block handles packet forwarding for normal scenarios in which there is no link failure 
             It tries to find the first available outlink to send the packet depending on 
             the number of available ports we have to have if statement. Loop is not supported!
             */
            if(meta.final_dst==1){
                hops_r.write((bit<32>) hdr.myTunnel.src_id, hdr.myTunnel.hops_1);
                ipv4_lpm.apply();
            }
            else
            {
                // We check packet sequence to find if the packet comes from changed link
                // or normal
                if (hdr.myTunnel.packet_seq != remoteseq) {
                        reverse_out_to_in(standard_metadata.ingress_port);
                    }


                // Are there any outlink to send the packets?
                // if YES, we check the direction of the packet in one if-else statement
                // ELSE we reverse all IN to OUT
                direction_r.read(dir_n, 2);
                if(dir_n==0 && standard_metadata.ingress_port != 1 || port_status_2 ==0 ){
                
                    
                        reverse_in_to_out(2);
                    
                    
                    }
                    

                 //direction==1
                 // at this stage, we are sure that there is at least one out link
                 // we received a packet from outlink and should check packet sequence
                 // if pkt.seq!=pkt.seq we send to one of outlinks else bounce back packet   

                if(direction==1){
                    
                        direction_r.read(dir_2, 2);
                        port_status_r.read(port_status_2,2);
                    
                        remote_seq_r.read(remoteseq,(bit<32>) standard_metadata.ingress_port);
                        if (hdr.myTunnel.packet_seq == remoteseq) {
                            //sends pkt back on the port it came from
                            send_on_outlink(standard_metadata.ingress_port);

                        }
                        //else we have to reverse all OUT to IN
                        // and send it from one of the new OUT links
                        else{
                            
                                direction_r.read(dir_2, 2);
                                port_status_r.read(port_status_2,2);
                            
                                 if (dir_2 == 1 && port_status_2 ==1 ) {
                                        //hdr.myTunnel.packet_seq=1;
                                        send_on_outlink(2);
                                    }
                            
                        }
                    }

                    //direction==0
                    // at this stage, we are sure that there is at least one out link
                    // and the packet should be forwarded through that link
                else
                {
                    
                    direction_r.read(dir_2, 2);
                    port_status_r.read(port_status_2,2);
                    
                     if (dir_2 == 1 && port_status_2 ==1 ) {
                            //hdr.myTunnel.packet_seq=1;
                            send_on_outlink(2);
                        }
                        

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
        packet.emit(hdr.myTunnel);
        packet.emit(hdr.ipv4);
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